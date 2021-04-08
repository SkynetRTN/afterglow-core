<template>
  <div class="container">
    <div v-if="client.icon" class="content">
      <img
        class="image"
        v-bind:src="client.icon"
        style="max-width: 125px; max-height: 125px; margin: auto;"
      />
    </div>

    <p class="content">
      <b>{{ client.name }}</b> is a third-party application which would like
      access to your Afterglow Core account. Only grant this access if you trust
      the third-party application with your Afterglow Core information and data
    </p>

    <p class="content">{{ client.description }}</p>

    <div class="field is-grouped is-grouped-right">
      <div class="control">
        <button v-on:click="denyApp()" class="button is-link">Deny</button>
      </div>
      <div class="control">
        <button v-on:click="grantApp()" class="button is-link">Allow</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from "vue-property-decorator";
import { OauthClient } from "../api/types";

@Component({
  name: "app-consent-form",
  components: {},
})
export default class AppConsentForm extends Vue {
  @Prop({ default: null })
  client: OauthClient;

  mounted() {}

  denyApp() {
    this.$emit("app-consent-denied", this.client.id);
  }

  grantApp() {
    this.$emit("app-consent-granted", this.client.id);
  }
}
</script>
