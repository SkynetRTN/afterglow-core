import Vue from "vue";
import Router from "vue-router";
import Home from "./views/Home.vue";
import AccessTokens from "./views/AccessTokens.vue";
import OauthClientAuthorizations from "./views/OauthClientAuthorizations.vue";

Vue.use(Router);

const routes = [
  {
    meta: {
      title: "Dashboard",
    },
    path: "/",
    name: "home",
    component: Home,
  },
  {
    meta: {
      title: "Access Tokens",
    },
    path: "/settings/tokens",
    name: "tokens",
    component: AccessTokens,
  },
  {
    meta: {
      title: "Third-Party Apps",
    },
    path: "/settings/apps",
    name: "apps",
    component: OauthClientAuthorizations,
  },
  {
    path: "/full-page",
    component: () =>
      import(/* webpackChunkName: "full-page" */ "./views/FullPage.vue"),
    children: [
      {
        meta: {
          title: "Login",
        },
        path: "/login",
        name: "login",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/Login.vue"
          ),
      },
      {
        meta: {
          title: "Consent",
        },
        path: "/oauth2/consent",
        name: "oauth2-consent",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/Oauth2Consent.vue"
          ),
      },
      {
        meta: {
          title: "Authorizing...",
        },
        path: "/oauth2/authorized",
        name: "oauth2-authorized",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/Oauth2Authorized.vue"
          ),
      },
      {
        meta: {
          title: "Password Recovery",
        },
        path: "/password-recovery",
        name: "password-recovery",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/PasswordRecovery.vue"
          ),
      },
      {
        meta: {
          title: "Error v.1",
        },
        path: "/error-in-card",
        name: "error-in-card",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/Error.vue"
          ),
      },
      {
        meta: {
          title: "Error v.2",
        },
        path: "/error-simple",
        name: "error-simple",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/Error.vue"
          ),
        props: { isInCard: false },
      },
      {
        meta: {
          title: "Lock screen",
        },
        path: "/lock-screen",
        name: "lock-screen",
        component: () =>
          import(
            /* webpackChunkName: "full-page" */ "./views/full-page/LockScreen.vue"
          ),
      },
    ],
  },
];
export default new Router({
  // mode: 'history',  // Enable this if you need.
  scrollBehavior: (to, from, savedPosition) => {
    if (savedPosition) {
      return savedPosition;
    } else {
      return { x: 0, y: 0 };
    }
  },
  base: process.env.BASE_URL,
  mode: "history",
  routes: routes,
});
