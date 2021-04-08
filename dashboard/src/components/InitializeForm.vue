<template>
  <form id="init-form" method="post" @submit="formSubmit">
    <div class="notification is-danger" v-if="errors.length">
      <ul>
        <li v-for="error in errors" v-bind:key="error">{{ error }}</li>
      </ul>
    </div>

    <div class="field">
      <label for="username" class="label">Username</label>
      <div class="control has-icons-left">
        <input id="username" name="username" v-model="username" type="text" value class="input" />
        <span class="icon is-small is-left">
          <i class="fas fa-user"></i>
        </span>
      </div>
    </div>
    <div class="field">
      <label for="password" class="label">Password</label>
      <div class="control has-icons-left">
        <input id="password" name="password" v-model="password" type="password" value class="input" />
        <span class="icon is-small is-left">
          <i class="fas fa-lock"></i>
        </span>
      </div>
    </div>
    <div class="field">
      <label for="confirmPassword" class="label">Confirm Password</label>
      <div class="control has-icons-left">
        <input
          id="confirmPassword"
          name="confirmPassword"
          v-model="confirmPassword"
          type="password"
          value
          class="input"
        />
        <span class="icon is-small is-left">
          <i class="fas fa-lock"></i>
        </span>
      </div>
    </div>
    <div class="field">
      <label for="email" class="label">Email</label>
      <div class="control has-icons-left">
        <input id="email" name="email" v-model="email" type="email" value class="input" />
        <span class="icon is-small is-left">
          <i class="fas fa-envelope"></i>
        </span>
      </div>
    </div>
    <div class="field is-grouped is-grouped-right">
      <div class="control">
        <a class="button is-link is-light" href="/">Cancel</a>
      </div>
      <div class="control">
        <button
          class="button is-link"
          :disabled="submitDisabled"
          v-bind:class="{ 'is-loading': loading }"
        >Submit</button>
      </div>
    </div>
  </form>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from "vue-property-decorator";
import CardComponent from "../components/CardComponent.vue";
import { appConfig } from "../config";
import { UserModule } from "../store/modules/user";
import { AppModule } from "../store/modules/app";
import { ajaxApiUrl } from "../api/api-client";

import axios from "axios";
import { getServerStatus } from "../api/server-status";

@Component({
  name: "initialize-form",
  components: { CardComponent },
})
export default class IniitalizeForm extends Vue {
  username: string = null;
  password: string = null;
  confirmPassword: string = null;
  email: string = null;
  loading = false;
  errors: string[] = []

  formSubmit(e) {
      e.preventDefault();
      
     
      this.errors = [];

      if (!this.username) {
        this.errors.push("Username required.");
      }
      if (!this.password) {
        this.errors.push("Password required.");
      }
      if (this.password != this.confirmPassword) {
        this.errors.push("Passwords do not match");
      }
      if (!this.email) {
        this.errors.push("Email address is required");
      }

      if (this.errors.length == 0) {
        this.loading = true;
        const requestOptions = {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        };

      axios.post(`${ajaxApiUrl}/initialize`, {
          username: this.username,
          password: this.password,
          email: this.email
        })
        .then((response) => {
          return getServerStatus().then(({data} )=> {
            AppModule.UpdateServerStatus()
          })
          
        })
        .catch((error) => {
          this.errors = [];
          var r = error.response;
          switch (r.status) {
            case 500: {
              this.errors.push("An unexpected error occurred");
              break;
            }
            case 400: {
              if (typeof r.data == "string") {
                this.errors.push(r.data);
              } else {
                for (var field in r.data) {
                  if (Array.isArray(r.data[field])) {
                    r.data[field].forEach(e => this.errors.push(e));
                  } else {
                    this.errors.push(r.data[field]);
                  }
                }
              }

              break;
            }
            default: {
              this.errors.push("An unexpected error occurred");
              break;
            }
          }
        })
        .finally(() => {
          this.loading = false;
        });
      }

      return;
    }

    get submitDisabled() {
      return this.loading;
    }

    get coreInitialized() {
      return AppModule.serverStatus?.initialized;
    }

    @Watch('coreInitialized') 
    onCoreInitializedChange(value: boolean, oldValue: boolean) {
      if(value) {
         let nextUrl = this.$route.query.next;


        if (!nextUrl || typeof(nextUrl) != 'string') {
            nextUrl = '/';
          }
          this.$router.push(nextUrl)
      }
    }
};
</script>