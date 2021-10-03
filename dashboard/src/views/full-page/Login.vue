<template>
  <div class="column has-text-centered">
    <div class="content">
      <a href="/">
        <img
          src="../../assets/logo-full.png"
          alt="Afterglow Logo"
          style="max-width: 450px"
        />
      </a>
    </div>

    <div
      v-if="!showInitializationForm"
      class="columns is-multiline is-centered"
    >
      <div class="column is-5-tablet is-4-desktop is-3-widescreen">
        <div class="panel has-text-left has-background-white">
          <p class="panel-heading">Log in</p>
          <div class="panel-block">
            <div class="container">
              <form @submit.prevent="submit" method="POST">
                <b-field label="Username">
                  <b-input
                    v-model="form.username"
                    name="username"
                    type="text"
                    required
                    autofocus
                  />
                </b-field>

                <b-field label="Password">
                  <b-input
                    v-model="form.password"
                    type="password"
                    name="password"
                    required
                  />
                </b-field>

                <b-field>
                  <b-checkbox
                    v-model="form.remember"
                    type="is-black"
                    class="is-thin"
                  >
                    Remember me
                  </b-checkbox>
                </b-field>

                <hr />

                <div v-if="error" class="notification is-danger">
                  {{ error }}
                </div>

                <b-field grouped>
                  <div class="control">
                    <button
                      type="submit"
                      class="button is-black"
                      :class="{ 'is-loading': isLoading }"
                    >
                      Login
                    </button>
                  </div>
                  <div class="control">
                    <router-link
                      to="/password-recovery"
                      class="button is-outlined is-black"
                    >
                      Forgot Password?
                    </router-link>
                  </div>
                </b-field>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="oauthPluginsLoading || oauthPlugins.length > 0"
        class="column is-5-tablet is-4-desktop is-3-widescreen"
      >
        <div class="panel has-text-left has-background-white">
          <p class="panel-heading">Login Services</p>
          <div
            v-for="plugin in oauthPlugins"
            v-bind:key="plugin.authorizeUrl"
            class="panel-block"
          >
            <div class="container">
              <a
                class="button is-normal is-fullwidth"
                v-bind:href="getAuthorizeUrl(plugin)"
              >
                <span
                  v-if="plugin.icon"
                  class="icon is-small"
                  style="margin-right: 0.75em"
                >
                  <img v-bind:src="'assets/' + plugin.icon" />
                </span>
                <span>{{ plugin.description }}</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="columns is-multiline is-centered">
      <div class="column is-7-tablet is-6-desktop is-5-widescreen">
        <div class="panel has-text-left has-background-white">
          <p class="panel-heading">Admin Account Initialization</p>
          <div class="panel-block">
            <div class="container">
              <initialize-form></initialize-form>
            </div>
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
import { ajaxApiUrl } from "../../api/api-client";
import { isValidUrl } from "../../utils/validate";

@Component({
  name: "Login",
  components: { CardComponent, InitializeForm },
})
export default class Login extends Vue {
  isLoading = false;
  isOauth = false;
  error = "";
  redirect: string = null;

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
    if (!AppModule.oauthPluginsLoaded && !AppModule.oauthPluginsLoading) {
      AppModule.LoadOauthPlugins();
    }
  }

  get oauthPlugins() {
    return AppModule.oauthPlugins;
  }

  get oauthPluginsLoading() {
    return AppModule.oauthPluginsLoading;
  }

  get showInitializationForm() {
    return !AppModule.serverStatus?.initialized;
  }

  getAuthorizeUrl(plugin: OauthPlugin) {
    let next = this.$route.query.next;
    let state = {
      plugin: plugin.id,
    };
    if (next) state["next"] = next;

    let redirectUri =
      window.location.origin +
      this.$router.resolve({ name: "oauth2-authorized" }).href;

    let params = new URLSearchParams();
    params.append("response_type", "code");
    params.append("state", JSON.stringify(state));
    params.append("client_id", plugin.clientId);
    params.append("redirect_uri", redirectUri);

    return `${plugin.authorizeUrl}?${params.toString()}`;
  }

  async submit() {
    let next: string = null;
    if (this.$route.query.next && typeof this.$route.query.next == "string") {
      next = this.$route.query.next as string;
    }
    this.isLoading = true;
    this.error = "";
    try {
      await UserModule.Login(this.form);
      // await this.$store.dispatch('Login', this.form)
      if (next && isValidUrl(next)) {
        window.location.href = next;
      } else {
        this.$router.push({
          name: next || "home",
        });
      }
    } catch (err) {
      if (err.status == 401) {
        this.error = "Invalid username or password";
      } else {
        this.error = "Unexpected error occurred";
      }
    } finally {
      this.isLoading = false;
    }
  }
}
</script>
