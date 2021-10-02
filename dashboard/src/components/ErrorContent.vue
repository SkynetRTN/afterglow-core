<template>
  <div>
    <div class="error-page-icon">
      <b-icon icon="power-plug" custom-size="default"/>
    </div>
    <div class="error-page-caption">
      <h1>Sample error</h1>
    </div>
    <div class="error-page-action">
      <div class="buttons is-centered">
        <button type="button" @click="emitGoBack" class="button is-black">
          Go Back
        </button>
        <slot name="buttons"/>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'ErrorContent'
})
export default class ErrorContent extends Vue {
  @Prop({
    type: String,
    default: 'power-plug'
  })
  icon;

  @Prop({
    type: String,
    default: 'Error'
  })
  title;

  emitGoBack() {
    this.$emit('go-back')
  }
}
</script>
