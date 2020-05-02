import { config } from '../config';
import { handleApiResponse } from '../util';

import axios from "axios";

export const userService = {
    login,
    getUser,
    getAuthorizedApps,
    removeAuthorizedApp
};


function login(username, password) {
    return axios.post("/users/login", {
        username: username,
        password: password
    })
    // .then(handleApiResponse)
}

function getUser(userId) {
    return axios.get(`/api/v1.0/users/${userId}`)
}

function getAuthorizedApps(userId) {
    return axios.get(`/api/v1.0/users/${userId}/authorized-apps`)
}

function removeAuthorizedApp(userId, appId) {
    return axios.delete(`/api/v1.0/users/${userId}/authorized-apps/${appId}`)
}
