import { apiClient, ajaxApiUrl } from "./api-client";
import { OauthClientAuthorization } from "./types";

export const getOauthClientAuthorizations = () =>
  apiClient.get<OauthClientAuthorization[]>(`${ajaxApiUrl}/app-authorizations`);

export const createOauthClientAuthorization = (clientId: string) =>
  apiClient.post<OauthClientAuthorization>(
    `${ajaxApiUrl}/app-authorizations?client_id=${clientId}`
  );

export const deleteOauthClientAuthorization = (id: number) =>
  apiClient.delete(`${ajaxApiUrl}/app-authorizations/${id}`);
