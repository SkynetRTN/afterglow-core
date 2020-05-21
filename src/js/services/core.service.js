import axios from "axios";
import { config } from '../config';

export const coreService = {
    login,
    getUser,
    createToken,
    getTokens,
    deleteToken,
    getAppAuthorizations,
    removeAppAuthorization,
    createAppAuthorization,
    getJobs,
};

let apiUrl = `${config.baseUrl}${config.apiPath}`;


function login(username, password) {
    return axios.post(`${config.baseUrl}/login`, {
        username: username,
        password: password
    })
    // .then(handleApiResponse)
}

function getUser(userId) {
    return axios.get(`${apiUrl}/users/${userId}`)
}


function createToken(token) {
    return axios.post(`${apiUrl}/tokens`, token);
}

function getTokens() {
    return axios.get(`${apiUrl}/tokens`);
}

function deleteToken(id) {
    return axios.delete(`${apiUrl}/tokens/${id}`);
}

function getAppAuthorizations() {
    return axios.get(`${apiUrl}/app-authorizations`)
}

function createAppAuthorization(appId) {
    return axios.post(`${apiUrl}/app-authorizations`, {
        client_id: appId
    })
}

function removeAppAuthorization(authorizationId) {
    return axios.delete(`${apiUrl}/app-authorizations/${authorizationId}`)
}


function getJobs(fields=null, page=null, perPage=null) {
    if(fields === null) {
        fields = ['id']
    }
    let params = [
        `include=${fields.join(',')}`
    ];
    if(page !== null && perPage !== null) {
        params = [
            ...params,
            `offset=${page*perPage}`,
            `limit=${perPage}`,
        ];
    }
    params = params.join('&');
    return axios.get(`${apiUrl}/jobs?${params}`, {withCredentials: true});
}