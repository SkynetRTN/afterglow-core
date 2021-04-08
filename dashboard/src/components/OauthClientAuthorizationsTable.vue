<template>
  <section>
    <b-table :data="authorizations" :loading="loading" :striped="true">
      <template slot-scope="props">
        <b-table-column field="note" label="Note">
          {{ props.row.client.name }}
        </b-table-column>

        <b-table-column field="options" label="Options" width="250">
          <button
            class="button is-danger"
            v-on:click="deleteAuthorization(props.row.id)"
          >
            Revoke Access
          </button>
        </b-table-column>
      </template>
      <template slot="empty">
        <section class="section">
          <div class="content has-text-grey has-text-centered">
            <p>
              <i class="fa fa-frown-open fa-3x is-large"></i>
            </p>
            <p>Nothing here.</p>
          </div>
        </section>
      </template>
    </b-table>
  </section>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from "vue-property-decorator";
import { OauthClientAuthorization } from "../api/types";

@Component({
  name: "oauth-client-authorizations-table",
  components: {},
})
export default class OauthClientAuthorizationsTable extends Vue {
  @Prop({ default: [] })
  authorizations: OauthClientAuthorization[];

  @Prop({ default: false })
  loading: boolean;

  mounted() {}

  deleteAuthorization(authorizationId) {
    this.$emit("delete-authorization", authorizationId);
  }
}
</script>
