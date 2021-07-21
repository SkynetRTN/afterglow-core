<template>
  <card-component title="Change Password" icon="lock">
    <form @submit.prevent="submit">
      <b-field horizontal label="Current password" message="Required. Your current password">
        <b-input name="password_current" type="password" v-model="form.password_current" required
                 autcomplete="current-password"/>
      </b-field>
      <hr>
      <b-field horizontal label="New password" message="Required. New password">
        <b-input name="password" type="password" v-model="form.password" required autocomplete="new-password"/>
      </b-field>
      <b-field horizontal label="Confirm password" message="Required. New password one more time">
        <b-input name="password_confirmation" type="password" v-model="form.password_confirmation" required
                 autocomplete="new-password"/>
      </b-field>
      <hr>
      <b-field horizontal>
        <div class="control">
          <button type="submit" class="button is-primary" :class="{'is-loading':isLoading}">
            Submit
          </button>
        </div>
      </b-field>
    </form>
  </card-component>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import CardComponent from './CardComponent.vue'
@Component({
  name: 'PasswordUpdateForm',

  components: {
    CardComponent
  }
})
export default class PasswordUpdateForm extends Vue {
  isLoading = false;

  form = {
    password_current: null,
    password: null,
    password_confirmation: null
  };

  submit() {
    this.isLoading = true
    setTimeout(() => {
      this.isLoading = false
      this.$buefy.snackbar.open({
        message: 'Updated',
        queue: false
      })
    }, 500)
  }
}
</script>
