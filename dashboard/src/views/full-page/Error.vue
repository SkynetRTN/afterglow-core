<template>
  <div class="has-text-centered">
    <card-component v-if="isInCard" title="Sample Error" icon="alert" :has-button-slot="true" :has-card-header-background="true">
      <router-link slot="button" to="/" class="button is-small">
        <b-icon icon="desktop-mac" custom-size="default"/>
      </router-link>

      <error-content title="Sample Error" @go-back="goBack"/>
    </card-component>

    <error-content v-else title="Sample Error" @go-back="goBack"/>

  </div>

</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import ErrorContent from '../../components/ErrorContent.vue'
import CardComponent from '../../components/CardComponent.vue'

@Component({
  name: 'Error',
  components: { CardComponent, ErrorContent }
})
export default class Error extends Vue {
  @Prop({
    type: Boolean,
    default: true
  })
  isInCard: boolean;

  goBack() {
    this.$router.go(-1)
  }
}
</script>
