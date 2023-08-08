export interface Oauth2Provider {
    id: string;
    icon: string;
    client_id: string;
    authorize_url: string;
    request_token_params: { [key: string]: string };
    description: string;
}