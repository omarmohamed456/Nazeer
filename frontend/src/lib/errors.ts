export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

export function toMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch') {
      return 'Could not reach the API. Is the backend running?'
    }
    return error.message
  }
  return 'Something went wrong. Please try again.'
}
