import { apiClient, ajaxApiUrl } from "./api-client";
import { AppAuthorization } from "./types";

export const getAppAuthorizations = () =>
  apiClient.get<AppAuthorization[]>(`${ajaxApiUrl}/app-authorizations`);

export const createAppAuthorization = (clientId: string) =>
  apiClient.post<AppAuthorization>(
    `${ajaxApiUrl}/app-authorizations?client_id=${clientId}`
  );

export const deleteAppAuthorization = (id: number) =>
  apiClient.delete(`${ajaxApiUrl}/app-authorizations/${id}`);
