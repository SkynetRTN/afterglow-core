<template>
  <div>
    <div class="columns is-multiline is-centered">
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
      </div>
    </div>
    <div class="columns is-centered">
      <div class="column is-half">
        <div class="panel has-text-left has-background-white">
          <p class="panel-heading">Third-Party App Consent</p>
          <div class="panel-block">
            <app-consent-form
              v-if="client && !error && !loading"
              :client="client"
              v-on:app-consent-denied="onDenied($event)"
              v-on:app-consent-granted="onGranted($event)"
            >
            </app-consent-form>
            <div v-else-if="error">
              {{ error }}
            </div>
            <div
              v-else
              style="position: relative; width: 100%; min-height: 100px;"
            >
              <b-loading
                :is-full-page="false"
                :active="loading"
                :can-cancel="false"
              ></b-loading>
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
import AppAuthorizationForm from "../../components/AppAuthorizationForm.vue";
import { getOauthClient } from "../../api/oauth-clients";
import { createAppAuthorization } from "../../api/app-authorizations";
import { OauthClient } from "../../api/types";
import { isValidUrl } from "../../utils/validate";

@Component({
  name: "AppConsent",
  components: { CardComponent, AppAuthorizationForm },
})
export default class AppConsent extends Vue {
  loading = true;
  error = "";
  client: OauthClient = null;
  next: string;

  mounted() {
    let clientId = this.$route.query.client_id;
    if (!clientId || typeof clientId != "string") {
      this.error = "Client ID is missing";
      return;
    }
    let next = this.$route.query.next;
    if (!next || typeof next != "string") {
      next = "/";
    }
    this.next = next;
    this.loading = true;
    getOauthClient(clientId)
      .then(({ data: client }) => {
        this.client = client;
        this.loading = false;
      })
      .catch((err) => {
        this.loading = false;
        this.error = "Unexpect error occurred";
      });
  }

  onDenied(id: string) {
    this.$router.push({ name: "home" });
  }

  onGranted(id: string) {
    this.loading = true;
    createAppAuthorization(this.client.id)
      .then(({ data: authorization }) => {
        this.loading = false;
        if (this.next && isValidUrl(this.next)) {
          window.location.href = this.next;
        } else {
          this.$router.push({
            name: this.next || "home",
          });
        }
      })
      .catch((err) => {
        this.loading = false;
      });
  }
}
</script>
