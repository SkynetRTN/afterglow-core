export interface ServerStatus {
  initialized: boolean;
  version: string;
}

export interface Role {
  id: number;
  name: string;
  description: string;
}

export interface Identity {
  id: number;
  name: string;
  userId: number;
  authMethod: string;
  data: any;
}

export interface User {
  id: number;
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  birthDate: Date;
  active: boolean;
  createdAt: Date;
  modifiedAt: Date;
  roles: Role[];
  settings: string;
  identities: Identity[];
}

export interface OauthPlugin {
  id: string;
  clientId: string;
  icon: string;
  description: string;
  authorizeUrl: string;
}

export interface OauthClientAuthorization {
  id: number;
  userId: number;
  clientId: string;
  client: OauthClient;
}

export interface OauthClient {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export interface TokenLtd {
  id: number;
  userId: string;
  tokenType: string;
  issuedAt: number;
  expiresIn: number;
  note: string;
}

export interface Token extends TokenLtd {
  accessToken: string;
}
