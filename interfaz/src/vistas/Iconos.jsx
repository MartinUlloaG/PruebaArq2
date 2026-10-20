// Íconos decorativos (aria-hidden): siempre acompañan a un texto, nunca lo reemplazan.

export function IconoError() {
  return (
    <svg className="icono" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 5.5v5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="10" cy="14.2" r="1.15" fill="currentColor" />
    </svg>
  )
}

export function IconoReloj() {
  return (
    <svg className="icono" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 5.5V10l3 2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

export function IconoCandado() {
  return (
    <svg className="icono icono--grande" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <rect x="4" y="9" width="12" height="8.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M6.8 9V6.5a3.2 3.2 0 0 1 6.4 0V9" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}
