import {
  VuexModule,
  Module,
  Action,
  Mutation,
  getModule,
} from "vuex-module-decorators";
import { login, logout, getUser, loginViaOauth2Plugin } from "../../api/users";
import {
  getSiteAuth,
  removeSiteAuth as clearAuthState,
  getUserId,
} from "../../utils/cookies";
import store from "../../store";
import { SSL_OP_NO_SESSION_RESUMPTION_ON_RENEGOTIATION } from "constants";
import { User } from "src/api/types";
import router from "../../router";
import { isValidUrl } from "../../utils/validate";

export interface IUserState {
  siteAuth: boolean;
  userId: string;
  user: User;
}

@Module({ dynamic: true, store, name: "user" })
class UserState extends VuexModule implements IUserState {
  public siteAuth = getSiteAuth() || false;
  public userId = getUserId() || "";
  public user: User = null;

  @Mutation
  private SET_SITE_AUTH(value: boolean) {
    this.siteAuth = value;
  }

  @Mutation
  private SET_USER_ID(value: string) {
    this.userId = value;
  }

  @Mutation
  private SET_USER(user: User) {
    this.user = user;
  }

  @Action({ rawError: true })
  public async Login(userInfo: { username: string; password: string }) {
    let { username, password } = userInfo;
    username = username.trim();
    const { data } = await login({ username, password });
    this.SET_SITE_AUTH(getSiteAuth());
    this.SET_USER_ID(getUserId());
  }

  @Action
  public LoginViaOauth2Plugin(payload: {
    pluginId: string;
    code: string;
    next: string;
    redirectUri: string;
  }) {
    let { pluginId, code, next, redirectUri } = payload;

    loginViaOauth2Plugin(pluginId, code, redirectUri)
      .then(() => {
        this.SET_SITE_AUTH(getSiteAuth());
        this.SET_USER_ID(getUserId());
        if (next && isValidUrl(next)) {
          window.location.href = next;
        } else {
          router.push({
            name: next || "home",
          });
        }
      })
      .catch((error) => router.push({ name: "login" }));
  }

  @Action
  public ResetAuthState() {
    clearAuthState();
    this.SET_SITE_AUTH(false);
    this.SET_USER_ID("");
    this.SET_USER(null);
  }

  @Action
  public async GetUser() {
    if (!this.siteAuth) {
      throw Error("GetUserInfo: invalid auth state");
    }
    const { data: user } = await getUser(this.userId);

    if (!user) {
      throw Error("Verification failed, please Login again.");
    }

    this.SET_USER(user);
  }

  @Action
  public async LogOut() {
    if (!this.siteAuth) {
      throw Error("Logout: Invalid auth state");
    }
    await logout();
    clearAuthState();
    this.SET_SITE_AUTH(false);
    this.SET_USER(null);
  }
}

export const UserModule = getModule(UserState);
