<template>
  <div class="aside-tools" :class="{'has-icon':!!icon}">
    <div class="aside-tools-label">
      <b-icon v-if="icon" :icon="icon" custom-size="default"/>
      <slot/>
    </div>
    <a v-if="hasClose" class="aside-close" @click="close">
      <b-icon icon="close" custom-size="default"/>
    </a>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'AsideTools'
})
export default class AsideTools extends Vue {
  @Prop({
    type: String,
    default: null
  })
  icon;

  @Prop({
    type: String,
    default: null
  })
  label;

  @Prop({
    type: Boolean,
    default: false
  })
  hasClose;

  close() {
    this.$emit('close')
  }
}
</script>
