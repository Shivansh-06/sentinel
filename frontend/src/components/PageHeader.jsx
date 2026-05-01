import React from 'react';
import styles from './PageHeader.module.css';

export default function PageHeader({ title, sub, action }) {
  return (
    <div className={styles.header}>
      <div>
        <h1 className={styles.title}>{title}</h1>
        {sub && <p className={styles.sub}>{sub}</p>}
      </div>
      {action && <div className={styles.actionSlot}>{action}</div>}
    </div>
  );
}
