<template>
  <section>
    <b-table :data="tokens" :loading="loading" :striped="true">
      <template slot-scope="props">
        <b-table-column field="note" label="Note">
          {{ props.row.note }}
        </b-table-column>

        <b-table-column field="options" label="Options" width="250">
          <button class="button is-danger" v-on:click="deleteToken(props.row.id)">
            Delete Token
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
import { getTokens, createToken, deleteToken } from "../api/tokens";
import { Token, TokenLtd } from "../api/types";

@Component({
  name: "token-table",
  components: {},
  filters: {
    truncate(value, length) {
      return value.length > length ? value.substr(0, length) + "..." : value;
    },
  },
})
export default class TokenTable extends Vue {
  @Prop({default: []})
  tokens: TokenLtd[];

  @Prop({default: false})
  loading: boolean;

  mounted() {
    
  }

  deleteToken(tokenId) {
    this.$emit('delete-token', tokenId)
  }
}
</script>
