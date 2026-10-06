import { statusLabel, type VerificationResult } from "../types/verification"
import ResultRow from "./ResultRow"

type VerificationResultsProps = {
  result: VerificationResult
}

function VerificationResults({ result }: VerificationResultsProps) {
  const counts = {
    match: result.fields.filter((field) => field.status === "MATCH").length,
    mismatch: result.fields.filter((field) => field.status === "MISMATCH").length,
    review: result.fields.filter((field) => field.status === "REVIEW").length,
  }
  const overall = result.overallStatus.toLowerCase()

  return (
    <section className="card result" aria-live="polite">
      <h2>Result</h2>
      <p className={`overall overall-${overall}`}>
        <span className={`badge badge-${overall}`}>{statusLabel(result.overallStatus)}</span>
        <span>{result.message}</span>
      </p>
      <ul className="totals">
        <li>{counts.match} match</li>
        <li>{counts.mismatch} mismatch</li>
        <li>{counts.review} needs review</li>
      </ul>
      <ul className="result-list">
        {result.fields.map((field) => (
          <ResultRow key={field.label} field={field} />
        ))}
      </ul>
    </section>
  )
}

export default VerificationResults
