import { apiClient, publicApiUrl, ajaxApiUrl } from "./api-client";
import { User } from "./types";

export const getUser = (userId: string, expand: Array<string> = []) =>
  apiClient.get<User>(`${publicApiUrl}/users/${userId}`);

export const login = (data: any) =>
  apiClient.post(`${ajaxApiUrl}/sessions`, data);

export const loginViaOauth2Plugin = (
  pluginId: string,
  code: string,
  redirectUri: string
) => {
  let params = new URLSearchParams();
  params.append("code", code);
  params.append("redirect_uri", redirectUri);

  return apiClient.get(
    `${ajaxApiUrl}/oauth2/providers/${pluginId}/authorized?${params.toString()}`
  );
};

export const logout = () => apiClient.delete(`${ajaxApiUrl}/sessions`);
