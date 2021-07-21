import { apiClient, ajaxApiUrl } from "./api-client";
import { User, OauthPlugin } from "./types";

export const getOauthPlugins = () =>
  apiClient.get<OauthPlugin[]>(`${ajaxApiUrl}/oauth2/providers`);
