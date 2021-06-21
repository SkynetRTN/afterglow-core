<template>
  <card-component title="Edit Profile" icon="account-circle">
    <form @submit.prevent="submit">
      <b-field horizontal label="Avatar">
        <file-picker/>
      </b-field>
      <hr>
      <b-field horizontal label="Name" message="Required. Your name">
        <b-input v-model="form.name" name="name" required/>
      </b-field>
      <b-field horizontal label="E-mail" message="Required. Your e-mail">
        <b-input v-model="form.email" name="email" type="email" required/>
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
import { mapState } from 'vuex'
import FilePicker from './FilePicker.vue'
import CardComponent from './CardComponent.vue'
import { UserModule } from "../store/modules/user";

@Component({
  name: 'ProfileUpdateForm',

  components: {
    CardComponent,
    FilePicker
  },

  watch: {
    userName (newValue) {
      // TODO FIX
      // this.form.name = newValue
    },
    userEmail (newValue) {
      // TODO FIX
      // this.form.email = newValue
    }
  }
})
export default class ProfileUpdateForm extends Vue {
  isFileUploaded = false;
  isLoading = false;

  form = {
    name: null,
    email: null
  };

  get userName() {
    return UserModule.user ? UserModule.user.username : ''
  }

  get userEmail() {
    return UserModule.user ? UserModule.user.email : ''
  }

  mounted() {
    this.form.name = this.userName
    this.form.email = this.userEmail
  }

  submit() {
    this.isLoading = true
    setTimeout(() => {
      this.isLoading = false
      this.$store.commit('user', this.form)
      this.$buefy.snackbar.open({
        message: 'Updated',
        queue: false
      })
    }, 500)
  }
}
</script>
