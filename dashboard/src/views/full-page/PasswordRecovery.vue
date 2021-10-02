<template>
  <card-component title="Password Recovery" icon="lock-open" :has-card-header-background="true" :has-button-slot="true">
    <router-link slot="button" to="/" class="button is-small">
      Dashboard
    </router-link>

    <form @submit.prevent="submit" method="POST">

      <b-field label="E-mail Address" message="E-mail used for registration">
        <b-input type="email" name="email" v-model="form.email" required autofocus/>
      </b-field>

      <hr>

      <b-field grouped>
        <div class="control">
          <button type="submit" class="button is-black" :class="{'is-loading':isLoading}">
            Send Reset Link
          </button>
        </div>
        <div class="control">
          <router-link to="/login" class="button is-black is-outlined">
            Back
          </router-link>
        </div>
      </b-field>
    </form>
  </card-component>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import CardComponent from '../../components/CardComponent.vue'

@Component({
  name: 'Login',
  components: { CardComponent }
})
export default class Login extends Vue {
  isLoading = false;
  isSuccess = false;

  form: {email: string} = {
    email: null
  };

  submit() {
    this.isLoading = true

    setTimeout(() => {
      this.form.email = null
      this.isLoading = false
      this.isSuccess = true

      this.$buefy.snackbar.open({
        message: 'Link sent',
        duration: 1000,
        queue: false
      })
    }, 750)
  }
}
</script>
