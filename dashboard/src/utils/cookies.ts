import Cookies from 'js-cookie'
import { appConfig } from '../config'

// App
const sidebarStatusKey = 'sidebar-status'
export const getSidebarStatus = () => Cookies.get(sidebarStatusKey)
export const setSidebarStatus = (sidebarStatus: string) => Cookies.set(sidebarStatusKey, sidebarStatus)

const mobileSidebarStatusKey = 'mobile-sidebar-status'
export const getMobileSidebarStatus = () => Cookies.get(mobileSidebarStatusKey)
export const setMobileSidebarStatus = (sidebarStatus: string) => Cookies.set(mobileSidebarStatusKey, sidebarStatus)

// CSRF
const csrfTokenKey = appConfig.csrfCookieName
if(!csrfTokenKey) {
    console.error("CSRF_COOKIE_NAME environment variable has not been set")
}
export const getCsrfToken = () => csrfTokenKey ? Cookies.get(csrfTokenKey): ''

// User
const siteAuthKey = appConfig.authCookieName
if(!siteAuthKey) {
    console.error("SITE_AUTH_COOKIE_NAME environment variable has not been set")
}
export const getSiteAuth = () => (siteAuthKey && Cookies.get(siteAuthKey)) ? true : false
export const removeSiteAuth = () => {
    if(siteAuthKey) {
        Cookies.remove(siteAuthKey);
    }
}

const userIdKey = appConfig.userIdCookieName
if(!userIdKey) {
    console.error("USER_ID_COOKIE_NAME environment variable has not been set")
}
export const getUserId = () => userIdKey ? Cookies.get(userIdKey) || '' : ''
export const removeUserId = () => {
    if(userIdKey) {
        Cookies.remove(userIdKey)
    }
}
