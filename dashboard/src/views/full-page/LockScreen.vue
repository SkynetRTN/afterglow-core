<template>
  <div class="has-text-centered">
    <user-avatar class="has-max-width is-aligned-center error-page-icon" />
    <div class="error-page-caption">
      <h1>{{ userName }}</h1>
    </div>
    <div class="error-page-action">
      <div v-if="!isPasswordInputActive" class="buttons is-centered">
        <button type="button" class="button is-black" @click="passwordActivate">Unlock</button>
      </div>
      <form @submit.prevent="submit" v-else>
        <b-field position="is-centered">
          <b-input ref="input" type="password" v-model="form.password" />
          <div class="control">
            <button
              type="submit"
              class="button is-black"
              :class="{'is-loading':isLoading}"
              :disabled="!form.password"
            >
              <b-icon icon="lock-open" custom-size="default" />
            </button>
          </div>
        </b-field>
      </form>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { mapState } from "vuex";
import UserAvatar from "../../components/UserAvatar.vue";
import { UserModule } from '../../store/modules/user';

@Component({
  name: "LockScreen",
  components: { UserAvatar }
})
export default class LockScreen extends Vue {
  isPasswordInputActive = false;
  isLoading = false;

  form : {password: string} = {
    password: null,
  };

  get userName() {
    return UserModule.user ? UserModule.user.username : ''
  }

  passwordActivate() {
    this.isPasswordInputActive = true;
    this.$nextTick(() => {
      (this.$refs.input as HTMLInputElement).focus();
    });
  }

  submit() {
    this.isLoading = true;
    setTimeout(() => {
      this.isLoading = false;
      this.$router.push("/");
    }, 750);
  }
}
</script>
