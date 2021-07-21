import { apiClient, ajaxApiUrl } from "./api-client";
import { OauthClient } from "./types";

export const getOauthClient = (id) =>
  apiClient.get<OauthClient>(`${ajaxApiUrl}/oauth2/clients/${id}`);
