import { apiClient, ajaxApiUrl } from './api-client'
import { ServerStatus } from './types'

export const getServerStatus = () =>
  apiClient.get<ServerStatus>(`${ajaxApiUrl}/server_status`)