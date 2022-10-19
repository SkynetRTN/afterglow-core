import router from "./router";
import NProgress from "nprogress";
import "nprogress/nprogress.css";
// import { Message } from 'element-ui'
import { Route } from "vue-router";
import { UserModule } from "./store/modules/user";
import Cookies from "js-cookie";

NProgress.configure({ showSpinner: false });

const whiteList = ["login", "oauth2-authorized"];

router.beforeEach(async (to: Route, _: Route, next: any) => {
  // Start progress bar
  NProgress.start();
  // Determine whether the user has logged in
  if (UserModule.siteAuth && UserModule.userId !== "") {
    if (to.name === "login") {
      // If is logged in, redirect to the home page or next from query
      let nextPath: string = "/";
      if (to.query.next && typeof to.query.next == "string") {
        nextPath = to.query.next as string;
      }
      next({ path: nextPath });
      NProgress.done();
    } else {
      // Check whether the user has obtained his permission roles
      if (!UserModule.user) {
        try {
          // Get user info, including roles
          await UserModule.GetUser();
          // Set the replace: true, so the navigation will not leave a history record
          next({ ...to, replace: true });
        } catch (err) {
          // Remove token and redirect to login page
          console.log(err);
          UserModule.ResetAuthState();
          // Message.error('There was an unexpected error when retrieving your user profile.')
          next(`/login?next=${to.name}`);
          NProgress.done();
        }
      } else {
        next();
      }
    }
  } else {
    // Has no token
    if (whiteList.indexOf(to.name) !== -1) {
      // In the free login whitelist, go directly
      next();
    } else {
      // Other pages that do not have permission to access are redirected to the login page.
      next(`/login?next=${to.name}`);
      NProgress.done();
    }
  }
});

router.afterEach((to: Route) => {
  // Finish progress bar
  NProgress.done();

  // set page title
  document.title = to.meta.title;
});
