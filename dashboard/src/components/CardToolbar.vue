<template>
  <div class="notification is-card-toolbar">
    <div class="level" :class="{'is-mobile':isMobile}">
      <div class="level-left">
        <div class="level-item">
          <slot name="left"/>
        </div>
      </div>
      <div class="level-right">
        <div class="level-item">
          <slot name="right"/>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'CardToolbar'
})
export default class CardToolbar extends Vue {
  @Prop({
    type: Boolean,
    default: false
  })
  isMobile;
}
</script>
