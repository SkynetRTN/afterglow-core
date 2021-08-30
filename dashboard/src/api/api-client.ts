import axios from "axios";
import { UserModule } from "../store/modules/user";
import Cookies from "js-cookie";
import { getCsrfToken } from "../utils/cookies";
import qs from "qs";
import camelCaseKeys from "camelcase-keys";
import { appConfig } from "../config";

export const publicApiUrl = `${appConfig.coreUrl}/api/v1`;
export const ajaxApiUrl = `${appConfig.coreUrl}/ajax`;

export const apiClient = axios.create({
  timeout: 5000,
  paramsSerializer: function (params) {
    return qs.stringify(params, { indices: false }); // param=value1&param=value2
  },
});

// Request interceptors
apiClient.interceptors.request.use(
  (config) => {
    if (getCsrfToken()) {
      config.headers[appConfig.csrfHeaderName] = getCsrfToken();
    }
    return config;
  },
  (error) => {
    Promise.reject(error);
  }
);

// Response interceptors
apiClient.interceptors.response.use(
  (response) => {
    return {
      ...response,
      data: camelCaseKeys(response.data.data, { deep: true }),
      links: response.data.links
    };
  },
  (error) => {
    if (error.response) {
      // const data = error.response.data;
      // if (data.type) {
      //   // if (error.response.status === 401 && data.type !== 'login_error' && data.type !== 'invalid_csrf') {
      //   //   // MessageBox.confirm(
      //   //   //   'You have been logged out or your session has expired, try to login again.',
      //   //   //   'Logged Out',
      //   //   //   {
      //   //   //     confirmButtonText: 'Login',
      //   //   //     cancelButtonText: 'Cancel',
      //   //   //     type: 'warning'
      //   //   //   }
      //   //   // ).then(() => {
      //   //     UserModule.ResetAuthState()
      //   //     location.reload() // To prevent bugs from vue-router
      //   //   // })
      //   // }
      //   return Promise.reject(Error(data.detail))
      // }

      return Promise.reject(error.response);
    } else if (error.request) {
      return Promise.reject(
        Error("An unexpected error occurred.  No response received.")
      );
    } else {
      return Promise.reject(
        Error("An unexpected error occurred.  Failed to process the request.")
      );
    }
  }
);
