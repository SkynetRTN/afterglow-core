<template>
  <section class="hero is-hero-bar is-main-hero">
    <div class="hero-body">
      <div class="level">
        <div class="level-left">
          <div class="level-item is-hero-avatar-item">
            <div class="image is-user-avatar">
              <img :src="userAvatar"/>
            </div>
          </div>
          <div class="level-item is-hero-content-item">
            <div>
              <h1 class="title is-spaced">Howdy, <b>{{ username }}</b></h1>
              <h3 class="subtitle">Last login <b>{{ lastLoginTimeString }}</b> from <b>{{ lastLoginIpString }}</b></h3>
              <p>You have <b>6 tasks</b> due today and <b>84 inquiries</b></p>
            </div>
          </div>
        </div>
        <div class="level-right">
          <div class="level-item">
            <router-link to="/profile" class="button is-light" title="Profile">
              <b-icon icon="account" custom-size="default"/>
              <span>Manage profile</span>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { mapState } from 'vuex'
import { UserModule } from "../store/modules/user";
@Component({
  name: 'HeroBarMain'
})
export default class HeroBarMain extends Vue {
  lastLoginTimeString = '12 mins ago';
  lastLoginIpString = '192.168.1.1';
  
  get username() {
    return UserModule.user ? UserModule.user.username : ''
  }

  get userAvatar() {
    return ""
  }


}
</script>
