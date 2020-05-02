import axios from "axios";
import { config } from '../config';

export const jobService = {
    getJobs
};


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
    return axios.get(`${config.apiUrl}/jobs?${params}`, {withCredentials: true});
}