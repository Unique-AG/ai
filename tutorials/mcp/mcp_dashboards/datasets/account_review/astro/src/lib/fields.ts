/** One label/value row in a client-page FieldGrid — see data/clientSections.ts. */
export interface Field {
  label: string;
  field: string;
  code?: boolean;
  na?: boolean;
}
