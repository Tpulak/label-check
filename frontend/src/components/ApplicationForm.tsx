import { applicationFields, type ApplicationInfo } from "../types/verification"

const GOVERNMENT_WARNING =
  "(1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."

type ApplicationFormProps = {
  values: ApplicationInfo
  onChange: (field: keyof ApplicationInfo, value: string) => void
  onVerify: () => void
  isChecking: boolean
}

function ApplicationForm({
  values,
  onChange,
  onVerify,
  isChecking,
}: ApplicationFormProps) {
  return (
    <section className="card" aria-labelledby="application-heading">
      <h2 id="application-heading">Application</h2>
      <p className="help">Type the information from the application.</p>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          onVerify()
        }}
      >
        {applicationFields.map((field) => (
          <div className="field" key={field.name}>
            <label htmlFor={`field-${field.name}`}>
              {field.label}
              <span className="example">Example: {field.example}</span>
            </label>
            <input
              id={`field-${field.name}`}
              name={field.name}
              type="text"
              value={values[field.name]}
              placeholder={field.example}
              autoComplete="off"
              required
              onChange={(event) => onChange(field.name, event.target.value)}
            />
          </div>
        ))}

        <div className="field">
          <p id="government-warning-label" className="fixed-label">
            Government Warning
          </p>
          <p className="fixed-text" aria-labelledby="government-warning-label">
            {GOVERNMENT_WARNING}
          </p>
        </div>

        <button type="submit" className="primary" disabled={isChecking}>
          {isChecking ? "Checking..." : "Verify label"}
        </button>
      </form>
    </section>
  )
}

export default ApplicationForm
