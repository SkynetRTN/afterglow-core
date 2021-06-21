<template>
  <div class="column has-text-centered">
    <div class="content">
      <a href="/">
        <img
          src="../../assets/logo-full.png"
          alt="Afterglow Logo"
          style="max-width: 450px;"
        />
      </a>
    </div>

    <div class="columns is-multiline is-centered">
      <div class="column has-text-centered">
        <div class="content">
          <b-progress v-if="!error" size="is-small"></b-progress>
          <div v-else class="notification is-danger">
            {{ error }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import CardComponent from "../../components/CardComponent.vue";
import InitializeForm from "../../components/InitializeForm.vue";
import { Dictionary } from "vue-router/types/router";
import { UserModule } from "../../store/modules/user";
import { AppModule } from "../../store/modules/app";
import { OauthPlugin } from "../../api/types";
import { appConfig } from "../../config";
import { ajaxApiUrl, apiClient } from "../../api/api-client";

@Component({
  name: "Login",
  components: { CardComponent, InitializeForm },
})
export default class Login extends Vue {
  error = "";
  redirect: string = null;
  otherQuery: Dictionary<string | string[]> = {};

  form: {
    username: string;
    password: string;
    remember: boolean;
  } = {
    username: null,
    password: null,
    remember: false,
  };

  mounted() {
    let code = this.$route.query.code;
    if (!code || typeof code != "string") {
      this.error = "Authorization code is required";
      return;
    }
    let state = this.$route.query.state;
    if (!state || typeof state != "string") {
      this.error = "Invalid state";
      return;
    }

    let stateObj = JSON.parse(state) as { plugin: string; next: string };
    if (!stateObj) {
      this.error = "Invalid state";
      return;
    }

    if (!stateObj.plugin) {
      this.error = "Plugin ID is required";
      return;
    }

    let next = stateObj.next;
    let pluginId = stateObj.plugin;
    let redirectUri =
      window.location.origin +
      this.$router.resolve({ name: "oauth2-authorized" }).href;

    UserModule.LoginViaOauth2Plugin({ pluginId, code, next, redirectUri });
  }
}
</script>
