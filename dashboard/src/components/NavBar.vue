<template>
  <nav v-show="isNavBarVisible" id="navbar-main" class="navbar is-fixed-top">
    <div class="navbar-brand">
      <a
        @click.prevent="menuToggle"
        :title="toggleTooltip"
        class="navbar-item is-desktop-icon-only is-hidden-touch"
      >
        <b-icon :icon="menuToggleIcon" />
      </a>
      <a
        class="navbar-item is-hidden-desktop"
        @click.prevent="menuToggleMobile"
      >
        <b-icon :icon="menuToggleMobileIcon" />
      </a>
      <div class="navbar-item no-left-space has-control">
        <!-- <div class="control">
          <input class="input" placeholder="Search everywhere...">
        </div> -->
      </div>
    </div>
    <div class="navbar-brand is-right">
      <a
        class="navbar-item navbar-item-menu-toggle is-hidden-desktop"
        @click.prevent="updatesToggle"
      >
        <b-icon icon="bell" custom-size="default" />
      </a>
      <a
        class="navbar-item navbar-item-menu-toggle is-hidden-desktop"
        @click.prevent="menuNavBarToggle"
      >
        <b-icon :icon="menuNavBarToggleIcon" custom-size="default" />
      </a>
    </div>
    <div
      class="navbar-menu fadeIn animated faster"
      :class="{ 'is-active': isMenuNavBarActive }"
    >
      <div v-if="user" class="navbar-end">
        <nav-bar-menu class="has-divider has-user-avatar">
          <img v-bind:src="avatarImageUrl" v-bind:alt="user.username" />
          <!-- <div class="is-user-name">
            <span>{{ user.username }}</span>
          </div> -->

          <div slot="dropdown" class="navbar-dropdown">
            <a class="navbar-item" @click="logout">
              <b-icon icon="logout" custom-size="default" />
              <span>Log Out</span>
            </a>
          </div>
        </nav-bar-menu>
        <a
          class="navbar-item is-desktop-icon-only"
          title="Log out"
          @click="logout"
        >
          <b-icon icon="logout" custom-size="default" />
          <span>Log out</span>
        </a>
      </div>
    </div>
  </nav>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { mapState } from "vuex";
import NavBarMenu from "./NavBarMenu.vue";
import UserAvatar from "./UserAvatar.vue";
import { UserModule } from "../store/modules/user";
import { AppModule } from "../store/modules/app";

@Component({
  name: "NavBar",

  components: {
    UserAvatar,
    NavBarMenu,
  },
})
export default class NavBar extends Vue {
  isMenuNavBarActive = false;

  get menuNavBarToggleIcon() {
    return this.isMenuNavBarActive ? "close" : "dots-vertical";
  }

  get menuToggleMobileIcon() {
    return this.isAsideMobileExpanded ? "backburger" : "forwardburger";
  }

  get menuToggleIcon() {
    return this.isAsideExpanded ? "backburger" : "forwardburger";
  }

  get toggleTooltip() {
    return this.isAsideExpanded ? "Collapse" : "Expand";
  }

  get isNavBarVisible() {
    return AppModule.isNavBarVisible;
  }

  get isAsideExpanded() {
    return AppModule.isAsideExpanded;
  }

  get isAsideMobileExpanded() {
    return AppModule.isAsideMobileExpanded;
  }

  get isAsideRightVisible() {
    return AppModule.isAsideRightVisible;
  }

  get userName() {
    return UserModule.user ? UserModule.user.username : "";
  }

  get hasUpdates() {
    return AppModule.hasUpdates;
  }

  get user() {
    return UserModule.user;
  }

  get avatarImageUrl() {
    let user = UserModule.user;
    if (!user) return "";
    let avatarId = user.username;
    if (user.firstName && user.lastName) {
      avatarId = `${user.firstName} ${user.lastName}`;
    } else if (user.firstName || user.lastName) {
      avatarId = user.firstName || user.lastName;
    }

    return `https://avatars.dicebear.com/v2/initials/${avatarId}.svg`;
  }

  menuToggle() {
    AppModule.ToggleSideBar();
  }

  menuToggleMobile() {
    AppModule.ToggleMobileSideBar();
  }

  menuNavBarToggle() {
    this.isMenuNavBarActive = !this.isMenuNavBarActive;
  }

  updatesToggle() {
    AppModule.ToggleRightSideBar();
  }

  async logout() {
    await UserModule.LogOut();
    this.$router.push({ name: "login" });
  }
}
</script>
