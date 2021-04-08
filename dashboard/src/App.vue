<template>
  <div id="app">
    <div v-if="!initialized">
      <section
        class="section hero is-fullheight is-error-section"
        style="background: #0a121f"
      >
        <div class="hero-body">
          <div class="container">
            <div class="column has-text-centered">
              <div class="content">
                <a href="/">
                  <img
                    src="./assets/logo-full.png"
                    alt="Afterglow Logo"
                    style="max-width: 450px;"
                  />
                </a>
              </div>

              <div class="column has-text-centered">
                <div class="content">
                  <b-progress
                    v-if="!initializationError"
                    size="is-small"
                  ></b-progress>
                  <div v-else class="notification is-danger">
                    {{ initializationError }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
    <div v-else>
      <nav-bar />
      <aside-menu
        :menu="menu"
        :menu-bottom="menuBottom"
        @menu-click="menuClick"
        :class="{ 'has-secondary': !!menuSecondary }"
      />
      <aside-menu
        v-if="menuSecondary"
        :menu="menuSecondary"
        :is-secondary="true"
        :label="menuSecondaryLabel"
        :icon="menuSecondaryIcon"
        @menu-click="menuClick"
        @close="menuSecondaryCloseClick"
      />
      <router-view />
      <aside-right />
      <footer-bar />
      <overlay />
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Watch } from "vue-property-decorator";
import NavBar from "./components/NavBar.vue";
import AsideMenu from "./components/AsideMenu.vue";
import FooterBar from "./components/FooterBar.vue";
import Overlay from "./components/Overlay.vue";
import AsideRight from "./components/AsideRight.vue";
import { AppModule } from "./store/modules/app";
import { UserModule } from "./store/modules/user";

@Component({
  name: "home",
  components: {
    AsideRight,
    Overlay,
    FooterBar,
    AsideMenu,
    NavBar,
  },
})
export default class extends Vue {
  private menuSecondary: any = null;
  private menuSecondaryLabel: string | null = null;
  private menuSecondaryIcon: string | null = null;

  get isOverlayVisible() {
    return true;
  }

  get initialized() {
    return AppModule.initialized;
  }

  get initializationError() {
    return AppModule.initializationError;
  }

  get menu() {
    return [
      "General",
      [
        {
          to: "/",
          icon: "desktop-mac",
          label: "Dashboard",
        },
      ],
      "Settings",
      [
        {
          to: "/settings/tokens",
          icon: "key",
          label: "Access Tokens",
        },
      ],
      // "Admin",
      // [
      //   {
      //     to: "/admin/users",
      //     icon: "account-group",
      //     label: "User Management",
      //   },
      // ]
    ];
  }

  get menuBottom() {
    return [
      {
        action: "logout",
        icon: "logout",
        label: "Log out",
        state: "info",
      },
    ];
  }

  private async menuClick(item: any) {
    if (item.menuSecondary) {
      this.menuSecondary = item.menuSecondary;
      this.menuSecondaryLabel = item.menuSecondaryLabel
        ? item.menuSecondaryLabel
        : null;
      this.menuSecondaryIcon = item.menuSecondaryIcon
        ? item.menuSecondaryIcon
        : null;

      this.$store.commit("asideActiveForcedKeyToggle", item);
      this.$store.commit("overlayToggle", true);
    } else if (item.action && item.action === "logout") {
      await UserModule.LogOut();
      this.$router.push(`/login?next=${this.$route.fullPath}`);
    }
  }

  private menuSecondaryCloseClick() {
    this.$store.commit("overlayToggle", false);
  }

  private menuSecondaryClose() {
    this.menuSecondary = this.menuSecondaryLabel = this.menuSecondaryIcon = null;
    this.$store.commit("asideActiveForcedKeyToggle", null);
  }

  @Watch("isOverlayVisible")
  private onIsOverlayVisibleChange(newValue: boolean) {
    if (!newValue) {
      this.menuSecondaryClose();
    }
  }

  mounted() {
    this.$store.dispatch("SetFullPageMode", true);
    this.$store.dispatch("ToggleRightSideBar", false);
    AppModule.Initialize();
  }

  @Watch("initialized")
  onInitializedChanged(value: boolean, oldValue: boolean) {
    if (value) {
      this.$store.dispatch("SetFullPageMode", false);
      this.$store.dispatch("ToggleSideBar", AppModule.isAsideExpanded);
      this.$store.dispatch(
        "ToggleMobileSideBar",
        AppModule.isAsideMobileExpanded
      );
    }
  }
}
</script>
