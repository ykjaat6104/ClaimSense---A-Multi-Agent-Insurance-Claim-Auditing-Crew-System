export default function DataWarehouse() {
  return (
    <div className="placeholder-page">
      <h1 className="page-title">Data warehouse</h1>
      <p className="page-sub">Structured exports for BI and model training (roadmap).</p>
      <div className="card">
        <ul>
          <li>Nightly JSONL snapshots of claims + mediator outputs</li>
          <li>Feature store for retraining fraud classifiers</li>
          <li>PII redaction profiles</li>
        </ul>
        <p className="page-sub">Use Reports → Export JSON per claim today; bulk pipelines land here.</p>
      </div>
    </div>
  );
}
