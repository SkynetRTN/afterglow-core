<template>
  <div class="is-user-avatar">
    <img :src="newUserAvatar" :alt="userName">
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import { mapState } from 'vuex'
import { UserModule } from "../store/modules/user";

@Component({
  name: 'UserAvatar'
})
export default class UserAvatar extends Vue {
  @Prop({
    type: String,
    default: null
  })
  avatar;

  get newUserAvatar() {
    if (this.avatar) {
      return this.avatar
    }

    if (this.userAvatar) {
      return this.userAvatar
    }

    let name = 'somename'

    if (this.userName) {
      name = this.userName.replace(/[^a-z0-9]+/i, '')
    }

    return `https://avatars.dicebear.com/v2/human/${name}.svg?options[mood][]=happy`
  }

  get userName() {
    return UserModule.user ? UserModule.user.username : ''
  }

  get userAvatar() {
    return '';
  }
}
</script>
