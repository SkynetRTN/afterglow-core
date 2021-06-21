import { apiClient, ajaxApiUrl } from "./api-client";
import { Token, TokenLtd } from "./types";

export const getTokens = () => apiClient.get<TokenLtd[]>(`${ajaxApiUrl}/tokens`);

export const createToken = (token: Partial<TokenLtd>) =>
  apiClient.post<Token>(`${ajaxApiUrl}/tokens`, token);

export const deleteToken = (id: number) => apiClient.delete(`${ajaxApiUrl}/tokens/${id}`);
