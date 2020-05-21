<template>
  <form id="login-form" method="post" @submit="formSubmit">
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
      <label for="rememberMe" class="checkbox">
        <input id="rememberMe" class="checkbox" v-model="rememberMe" type="checkbox" /> Remember me
      </label>
    </div>
    <div class="field is-grouped is-grouped-right">
      <div class="control">
        <a class="button is-link is-light" :href="cancelUrl">Cancel</a>
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

<script>
import { coreService } from "../services";

export default {
  data: function() {
    return {
      username: null,
      password: null,
      keepSignedIn: false,
      loading: false,
      errors: []
    };
  },
  props: ["nextUrl", "cancelUrl"],
  methods: {
    formSubmit: function(e) {
      e.preventDefault();

      this.errors = [];

      if (!this.username) {
        this.errors.push("Username required.");
      }
      if (!this.password) {
        this.errors.push("Password required.");
      }

      if (this.errors.length == 0) {
        this.loading = true;
        coreService
          .login(this.username, this.password)
          .then(() => {
            if (this.nextUrl) window.location = this.nextUrl;
          })
          .catch(error => {
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
  },
  computed: {
    submitDisabled: function() {
      return this.loading;
    }
  }
};
</script>