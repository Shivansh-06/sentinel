import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sanctioned_entity import SanctionedEntity
from app.workers.normalizer import normalize_name

logger = logging.getLogger(__name__)

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
UN_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

sync_engine = create_engine(settings.sync_database_url)


def fetch_xml(url: str) -> bytes:
    """
    Downloads XML feed with a generous timeout.
    OFAC's sdn.xml is ~7MB, UN list is ~2MB.
    """
    logger.info(f"Fetching sanctions list from {url}")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
    logger.info(f"Downloaded {len(response.content)} bytes from {url}")
    return response.content


def parse_ofac_sdn(xml_bytes: bytes) -> list[dict]:
    """
    Parses OFAC SDN XML into a list of entity dicts.

    OFAC XML structure:
    <sdnList>
      <sdnEntry>
        <uid>...</uid>
        <lastName>PUTIN</lastName>
        <firstName>VLADIMIR</firstName>
        <sdnType>Individual</sdnType>
        <programList><program>UKRAINE-EO13662</program></programList>
        <akaList>
          <aka><lastName>ПУТИН</lastName>...</aka>
        </akaList>
      </sdnEntry>
    </sdnList>

    We extract both primary names AND all AKAs — a sanctioned person
    might be listed under multiple name variants and we want to catch all of them.
    """
    root = ET.fromstring(xml_bytes)
    ns = {"ofac": "https://home.treasury.gov/system/files/126/ins.xsd"}

    # Try with namespace first, fall back to no namespace
    entries = root.findall(".//ofac:sdnEntry", ns)
    if not entries:
        entries = root.findall(".//sdnEntry")

    results = []

    for entry in entries:
        def get_text(tag):
            el = entry.find(f"ofac:{tag}", ns) or entry.find(tag)
            return el.text.strip() if el is not None and el.text else None

        uid = get_text("uid")
        last_name = get_text("lastName") or ""
        first_name = get_text("firstName") or ""
        sdn_type = get_text("sdnType") or "unknown"

        primary_name = f"{first_name} {last_name}".strip() if first_name else last_name

        programs = []
        prog_list = entry.find("ofac:programList", ns) or entry.find("programList")
        if prog_list is not None:
            for prog in prog_list:
                if prog.text:
                    programs.append(prog.text.strip())

        if primary_name:
            results.append({
                "source": "OFAC",
                "source_id": uid,
                "primary_name": primary_name,
                "normalized_name": normalize_name(primary_name),
                "entity_type": sdn_type.lower(),
                "program": ", ".join(programs) if programs else None,
            })

        # Extract AKAs as separate entries — each alias is a potential match
        aka_list = entry.find("ofac:akaList", ns) or entry.find("akaList")
        if aka_list is not None:
            for aka in aka_list:
                aka_last = None
                aka_first = None
                for child in aka:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag == "lastName" and child.text:
                        aka_last = child.text.strip()
                    elif tag == "firstName" and child.text:
                        aka_first = child.text.strip()

                aka_name = f"{aka_first} {aka_last}".strip() if aka_first else aka_last
                if aka_name and aka_name != primary_name:
                    results.append({
                        "source": "OFAC",
                        "source_id": f"{uid}_aka",
                        "primary_name": aka_name,
                        "normalized_name": normalize_name(aka_name),
                        "entity_type": sdn_type.lower(),
                        "program": ", ".join(programs) if programs else None,
                    })

    logger.info(f"Parsed {len(results)} OFAC entries (including AKAs)")
    return results


def parse_un_list(xml_bytes: bytes) -> list[dict]:
    """
    Parses UN Security Council consolidated sanctions XML.

    UN XML structure (simplified):
    <CONSOLIDATED_LIST>
      <INDIVIDUALS>
        <INDIVIDUAL>
          <DATAID>...</DATAID>
          <FIRST_NAME>...</FIRST_NAME>
          <SECOND_NAME>...</SECOND_NAME>
          <THIRD_NAME>...</THIRD_NAME>
          <UN_LIST_TYPE>...</UN_LIST_TYPE>
          <INDIVIDUAL_ALIAS>
            <ALIAS_NAME>...</ALIAS_NAME>
          </INDIVIDUAL_ALIAS>
        </INDIVIDUAL>
      </INDIVIDUALS>
      <ENTITIES>
        <ENTITY>
          <DATAID>...</DATAID>
          <FIRST_NAME>...</FIRST_NAME>
          <UN_LIST_TYPE>...</UN_LIST_TYPE>
        </ENTITY>
      </ENTITIES>
    </CONSOLIDATED_LIST>
    """
    root = ET.fromstring(xml_bytes)
    results = []

    def extract_text(element, tag):
        el = element.find(tag)
        return el.text.strip() if el is not None and el.text else None

    for individual in root.findall(".//INDIVIDUAL"):
        data_id = extract_text(individual, "DATAID")
        parts = [
            extract_text(individual, "FIRST_NAME"),
            extract_text(individual, "SECOND_NAME"),
            extract_text(individual, "THIRD_NAME"),
            extract_text(individual, "FOURTH_NAME"),
        ]
        name_parts = [p for p in parts if p]
        if not name_parts:
            continue

        primary_name = " ".join(name_parts)
        list_type = extract_text(individual, "UN_LIST_TYPE") or "UN"

        results.append({
            "source": "UN",
            "source_id": data_id,
            "primary_name": primary_name,
            "normalized_name": normalize_name(primary_name),
            "entity_type": "individual",
            "program": list_type,
        })

        for alias in individual.findall(".//INDIVIDUAL_ALIAS"):
            alias_name = extract_text(alias, "ALIAS_NAME")
            if alias_name and alias_name != primary_name:
                results.append({
                    "source": "UN",
                    "source_id": f"{data_id}_aka",
                    "primary_name": alias_name,
                    "normalized_name": normalize_name(alias_name),
                    "entity_type": "individual",
                    "program": list_type,
                })

    for entity in root.findall(".//ENTITY"):
        data_id = extract_text(entity, "DATAID")
        name = extract_text(entity, "FIRST_NAME")
        if not name:
            continue
        list_type = extract_text(entity, "UN_LIST_TYPE") or "UN"

        results.append({
            "source": "UN",
            "source_id": data_id,
            "primary_name": name,
            "normalized_name": normalize_name(name),
            "entity_type": "organization",
            "program": list_type,
        })

    logger.info(f"Parsed {len(results)} UN entries (including aliases)")
    return results


def sync_sanctions_lists() -> dict:
    """
    Full refresh of sanctions data. Deletes existing records for each
    source and replaces with fresh data.

    Why delete-and-replace rather than upsert: sanctions lists are
    authoritative snapshots. An entry removed from OFAC should be
    removed from your DB too — upsert wouldn't catch deletions.
    """
    results = {"ofac": 0, "un": 0, "errors": []}

    with Session(sync_engine) as session:
        try:
            ofac_xml = fetch_xml(OFAC_SDN_URL)
            ofac_entries = parse_ofac_sdn(ofac_xml)

            session.execute(delete(SanctionedEntity).where(
                SanctionedEntity.source == "OFAC"
            ))

            for entry in ofac_entries:
                session.add(SanctionedEntity(**entry))

            session.commit()
            results["ofac"] = len(ofac_entries)
            logger.info(f"Synced {len(ofac_entries)} OFAC entries")

        except Exception as e:
            logger.error(f"OFAC sync failed: {e}")
            results["errors"].append(f"OFAC: {str(e)}")
            session.rollback()

        try:
            un_xml = fetch_xml(UN_URL)
            un_entries = parse_un_list(un_xml)

            session.execute(delete(SanctionedEntity).where(
                SanctionedEntity.source == "UN"
            ))

            for entry in un_entries:
                session.add(SanctionedEntity(**entry))

            session.commit()
            results["un"] = len(un_entries)
            logger.info(f"Synced {len(un_entries)} UN entries")

        except Exception as e:
            logger.error(f"UN sync failed: {e}")
            results["errors"].append(f"UN: {str(e)}")
            session.rollback()

    return results