import { statusLabel, type FieldResult } from "../types/verification"

type ResultRowProps = {
  field: FieldResult
}

function ResultRow({ field }: ResultRowProps) {
  const status = field.status.toLowerCase()

  return (
    <li className={`result-${status}`}>
      <h3>{field.label}</h3>
      <p>
        <span className="result-tag">Application</span>
        {field.applicationValue}
      </p>
      <p>
        <span className="result-tag">Label</span>
        {field.labelValue ?? "Could not read"}
      </p>
      <p className={`badge badge-${status}`}>{statusLabel(field.status)}</p>
      <p className="help">{field.note}</p>
    </li>
  )
}

export default ResultRow
