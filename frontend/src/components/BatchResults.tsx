import { statusLabel, type VerificationResult } from "../types/verification"
import VerificationResults from "./VerificationResults"

export type FinishedLabel = {
  filename: string
  error: string | null
  result: VerificationResult | null
}

type BatchResultsProps = {
  items: FinishedLabel[]
  plannedCount: number
  stopped: boolean
  selectedFilename: string | null
  onSelect: (filename: string) => void
}

function BatchResults({
  items,
  plannedCount,
  stopped,
  selectedFilename,
  onSelect,
}: BatchResultsProps) {
  const counts = {
    match: items.filter((item) => item.result?.overallStatus === "MATCH").length,
    mismatch: items.filter((item) => item.result?.overallStatus === "MISMATCH").length,
    review: items.filter((item) => item.result?.overallStatus === "REVIEW").length,
    failed: items.filter((item) => item.error).length,
  }
  const selected = items.find((item) => item.filename === selectedFilename) ?? null

  return (
    <section className="card result" aria-live="polite">
      <h2>Batch result</h2>
      <p className="help">
        {stopped
          ? `Stopped after ${items.length} of ${plannedCount} labels.`
          : `${items.length} of ${plannedCount} labels finished.`}
      </p>
      <ul className="totals">
        <li>{counts.match} match</li>
        <li>{counts.mismatch} mismatch</li>
        <li>{counts.review} needs review</li>
        <li>{counts.failed} could not check</li>
      </ul>
      <ul className="batch-list">
        {items.map((item) => {
          const status = item.error ? "failed" : item.result?.overallStatus.toLowerCase()
          const label = item.error ? "Could not check" : statusLabel(item.result!.overallStatus)
          return (
            <li key={item.filename}>
              <button
                type="button"
                className={
                  item.filename === selectedFilename ? "batch-select selected" : "batch-select"
                }
                onClick={() => onSelect(item.filename)}
              >
                <span>{item.filename}</span>
                <span className={`badge badge-${status}`}>{label}</span>
              </button>
            </li>
          )
        })}
      </ul>
      {selected?.error ? (
        <p className="error" role="alert">
          {selected.error}
        </p>
      ) : null}
      {selected?.result ? <VerificationResults result={selected.result} /> : null}
    </section>
  )
}

export default BatchResults
