import {
  VuexModule,
  Module,
  Mutation,
  Action,
  getModule,
} from "vuex-module-decorators";
import each from "lodash/each";
import {
  getSidebarStatus,
  setSidebarStatus,
  getMobileSidebarStatus,
  setMobileSidebarStatus,
} from "../../utils/cookies";
import store from "../../store";
import { OauthPlugin, ServerStatus } from "../../api/types";
import { getOauthPlugins } from "../../api/oauth-plugins";
import { getServerStatus } from "../../api/server-status";

export enum DeviceType {
  Mobile,
  Desktop,
}

export interface IAppState {
  initialized: boolean;
  initializationError: string;
  serverStatus: ServerStatus;
  device: DeviceType;
  isNavBarVisible: boolean;
  isFooterBarVisible: boolean;
  isAsideVisible: boolean;
  isAsideExpanded: boolean;
  isAsideMobileExpanded: boolean;
  asideActiveForcedKey: string | null;
  isAsideRightVisible: boolean;
  hasUpdates: boolean;
  isOverlayVisible: boolean;
  oauthPluginsLoaded: boolean;
  oauthPluginsLoading: boolean;
  oauthPlugins: OauthPlugin[];
}

@Module({ dynamic: true, store, name: "app" })
class App extends VuexModule implements IAppState {
  public initialized = false;
  public initializationError = "";
  public serverStatus: ServerStatus = null;
  public isNavBarVisible = true;
  public isFooterBarVisible = true;
  public isAsideVisible = true;
  public isAsideExpanded = getSidebarStatus() !== "closed";
  public isAsideMobileExpanded = getMobileSidebarStatus() !== "closed";
  public asideActiveForcedKey = null;
  public isAsideRightVisible = false;
  public hasUpdates = false;
  public isOverlayVisible = false;
  public device = DeviceType.Desktop;
  public oauthPlugins = [];
  public oauthPluginsLoaded: false;
  public oauthPluginsLoading: false;

  @Mutation
  private TOGGLE_SIDEBAR(value: boolean | null = null) {
    const htmlAsideClassName = "has-aside-expanded";
    if (value === null) value = !this.isAsideExpanded;
    this.isAsideExpanded = value;
    if (value) {
      setSidebarStatus("opened");
      document.documentElement.classList.add(htmlAsideClassName);
    } else {
      setSidebarStatus("closed");
      document.documentElement.classList.remove(htmlAsideClassName);
    }
  }

  @Mutation
  private TOGGLE_MOBILE_SIDEBAR(value: boolean | null = null) {
    const htmlAsideClassName = "has-aside-mobile-expanded";
    if (value === null) value = !this.isAsideMobileExpanded;
    this.isAsideMobileExpanded = value;
    if (value) {
      setMobileSidebarStatus("opened");
      document.documentElement.classList.add(htmlAsideClassName);
    } else {
      setMobileSidebarStatus("closed");
      document.documentElement.classList.remove(htmlAsideClassName);
    }
  }

  @Mutation
  private TOGGLE_RIGHT_SIDEBAR(value: boolean | null = null) {
    const htmlClassName = "has-aside-right";
    if (value === null) value = !this.isAsideRightVisible;
    this.isAsideRightVisible = value;
    this.hasUpdates = false;
    if (value) {
      document.documentElement.classList.add(htmlClassName);
    } else {
      document.documentElement.classList.remove(htmlClassName);
    }
  }

  @Mutation
  private SET_FULL_PAGE_MODE(value: boolean) {
    this.isNavBarVisible = !value;
    this.isAsideVisible = !value;
    this.isFooterBarVisible = !value;

    each(["has-aside-left", "has-navbar-fixed-top"], (htmlClass: any) => {
      if (value) {
        document.documentElement.classList.remove(htmlClass);
      } else {
        document.documentElement.classList.add(htmlClass);
      }
    });
  }

  @Mutation
  private TOGGLE_DEVICE(device: DeviceType) {
    this.device = device;
  }

  @Mutation
  private SET_OAUTH_PLUGINS(plugins: OauthPlugin[]) {
    this.oauthPlugins = plugins;
  }

  @Mutation
  private SET_INITIALIZED(value: boolean) {
    this.initialized = value;
  }

  @Mutation
  private SET_INITIALIZATION_ERROR(error: string) {
    this.initializationError = error;
  }

  @Mutation
  private SET_SERVER_STATUS(status: ServerStatus) {
    this.serverStatus = status;
  }

  @Action
  public ToggleSideBar(state: boolean | null = null) {
    this.TOGGLE_SIDEBAR(state);
    this.TOGGLE_MOBILE_SIDEBAR(state);
  }

  @Action
  public ToggleMobileSideBar(state: boolean | null = null) {
    this.TOGGLE_MOBILE_SIDEBAR(state);
    this.TOGGLE_SIDEBAR(state);
  }

  @Action
  public ToggleRightSideBar(state: boolean | null = null) {
    this.TOGGLE_RIGHT_SIDEBAR(state);
  }

  @Action
  public SetFullPageMode(state: boolean) {
    this.SET_FULL_PAGE_MODE(state);
  }

  @Action
  public ToggleDevice(device: DeviceType) {
    this.TOGGLE_DEVICE(device);
  }

  @Action
  public async LoadOauthPlugins() {
    const { data } = await getOauthPlugins();
    this.SET_OAUTH_PLUGINS(data);
  }

  @Action
  public UpdateServerStatus() {
    getServerStatus()
      .then(({ data }) => {
        if (data) {
          this.SET_SERVER_STATUS(data);
        }
      })
      .catch((err) => {});
  }

  @Action
  public Initialize() {
    getServerStatus()
      .then((resp) => {
        if (!resp.data) {
          this.SET_INITIALIZATION_ERROR("Could not connect to the server.");
        } else {
          // resp.data.initialized = false;
          this.SET_SERVER_STATUS(resp.data);
          this.SET_INITIALIZED(true);
        }
      })
      .catch((err) => {
        this.SET_INITIALIZATION_ERROR("Could not connect to the server.");
      });
  }
}

export const AppModule = getModule(App);
