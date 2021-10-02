<template>
  <button type="button" class="button is-small" :class="{'is-loading':isLoading}" @click.prevent="click">
    <b-icon :icon="icon" custom-size="default"/>
    <span>{{ label }}</span>
  </button>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'RefreshButton'
})
export default class RefreshButton extends Vue {
  @Prop({
    type: String,
    default: 'refresh'
  })
  icon;

  @Prop({
    type: String,
    default: 'Refresh'
  })
  label;

  @Prop({
    type: Boolean,
    default: false
  })
  isLoading;

  click(e) {
    this.$emit('button-click', e)
  }
}
</script>
