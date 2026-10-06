import type {
  ApplicationInfo,
  VerificationResult,
} from "../types/verification"

// Empty on purpose. Locally, Vite forwards this to the backend.
// When the site is deployed, the page and the backend share one address.
const API_BASE = ""

type ServerField = {
  label: string
  application_value: string
  label_value: string | null
  status: VerificationResult["fields"][number]["status"]
  note: string
}

type ServerResponse = {
  image_name: string
  message: string
  overall_status: VerificationResult["overallStatus"]
  processing_ms: number
  fields: ServerField[]
}

export async function verifyLabel(
  image: File,
  application: ApplicationInfo,
): Promise<VerificationResult> {
  const body = new FormData()
  body.append("image", image)
  ;(Object.keys(application) as (keyof ApplicationInfo)[]).forEach((field) => {
    body.append(field, application[field])
  })

  let response: Response
  try {
    response = await fetch(`${API_BASE}/verify`, {
      method: "POST",
      body,
    })
  } catch {
    throw new Error("The server is not running. Start it, then try again.")
  }

  if (!response.ok) {
    let message = "The server could not check this label."
    try {
      const problem = (await response.json()) as { detail?: unknown }
      if (typeof problem.detail === "string") message = problem.detail
    } catch {
      // The server sent an error without JSON.
    }
    throw new Error(message)
  }

  const data = (await response.json()) as ServerResponse
  return {
    imageName: data.image_name,
    message: data.message,
    overallStatus: data.overall_status,
    processingMs: data.processing_ms,
    fields: data.fields.map((field) => ({
      label: field.label,
      applicationValue: field.application_value,
      labelValue: field.label_value,
      status: field.status,
      note: field.note,
    })),
  }
}
