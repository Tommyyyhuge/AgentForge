import type { ApiError, ApiResponse } from '../types'

type ErrorLike = {
  response?: {
    data?: unknown
  }
}

export function unwrapApiData<T>(body: ApiResponse<T> | T): T {
  if (
    body &&
    typeof body === 'object' &&
    'success' in body &&
    body.success === true
  ) {
    return body.data
  }
  return body as T
}

function asApiError(value: unknown): ApiError | null {
  if (
    value &&
    typeof value === 'object' &&
    'success' in value &&
    value.success === false &&
    'error' in value
  ) {
    return value as ApiError
  }
  return null
}

export function getApiErrorMessage(
  error: unknown,
  fallback = '操作失败，请稍后重试',
): string {
  const directError = asApiError(error)
  if (directError?.error?.message) {
    return directError.error.message
  }

  if (error && typeof error === 'object' && 'response' in error) {
    const responseData = (error as ErrorLike).response?.data
    const responseError = asApiError(responseData)
    if (responseError?.error?.message) {
      return responseError.error.message
    }
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallback
}
