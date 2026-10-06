export type ApplicationFieldName =
  | "brand_name"
  | "class_type"
  | "alcohol_content"
  | "net_contents"
  | "producer"

export type ApplicationInfo = Record<ApplicationFieldName, string>

export type FieldStatus = "MATCH" | "MISMATCH" | "REVIEW"

export type FieldResult = {
  label: string
  applicationValue: string
  labelValue: string | null
  status: FieldStatus
  note: string
}

export type VerificationResult = {
  imageName: string
  message: string
  overallStatus: FieldStatus
  processingMs: number
  fields: FieldResult[]
}

export const applicationFields: {
  name: ApplicationFieldName
  label: string
  example: string
}[] = [
  {
    name: "brand_name",
    label: "Brand name",
    example: "OLD TOM DISTILLERY",
  },
  {
    name: "class_type",
    label: "Class / type",
    example: "Kentucky Straight Bourbon Whiskey",
  },
  {
    name: "alcohol_content",
    label: "Alcohol content",
    example: "45%",
  },
  {
    name: "net_contents",
    label: "Net contents",
    example: "750 mL",
  },
  {
    name: "producer",
    label: "Producer name and address",
    example: "Old Tom Distillery, Louisville, KY",
  },
]

export const emptyApplication: ApplicationInfo = {
  brand_name: "",
  class_type: "",
  alcohol_content: "",
  net_contents: "",
  producer: "",
}

export function statusLabel(status: FieldStatus): string {
  if (status === "MATCH") return "Match"
  if (status === "MISMATCH") return "Mismatch"
  return "Needs review"
}
