<template>
  <div class="card" :class="{'has-height-medium':isScrollable, 'has-card-header-background':hasCardHeaderBackground}">
    <header v-if="title || hasTitleSlot" class="card-header">
      <p class="card-header-title">
        <b-icon v-if="icon" :icon="icon" custom-size="default"/>
        <slot v-if="hasTitleSlot" name="title"/>
        <span v-else-if="title">{{ title }}</span>
      </p>
      <slot v-if="hasButtonSlot" name="button"/>
      <a v-else-if="headerIcon" href="#" class="card-header-icon" aria-label="more options" @click.prevent="headerIconClick">
        <b-icon :icon="headerIcon" custom-size="default"/>
      </a>
    </header>
    <slot name="toolbar"/>
    <div ref="cardContent" class="card-content">
      <slot/>
    </div>
    <footer v-if="hasFooterSlot" class="card-footer">
      <slot name="footer"/>
    </footer>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import PerfectScrollbar from 'perfect-scrollbar'
@Component({
  name: 'CardComponent'
})
export default class CardComponent extends Vue {
  ps: PerfectScrollbar;
  @Prop({
    type: String,
    default: null
  })
  title;

  @Prop({
    type: String,
    default: null
  })
  icon;

  @Prop({
    type: String,
    default: null
  })
  headerIcon;

  @Prop({
    type: Boolean,
    default: false
  })
  hasTitleSlot;

  @Prop({
    type: Boolean,
    default: false
  })
  hasButtonSlot;

  @Prop({
    type: Boolean,
    default: false
  })
  hasFooterSlot;

  @Prop({
    type: Boolean,
    default: false
  })
  hasCardHeaderBackground;

  @Prop({
    type: Boolean,
    default: false
  })
  isScrollable;

  headerIconClick() {
    this.$emit('header-icon-click')
  }

  mounted() {
    if (this.isScrollable) {
      this.ps = new PerfectScrollbar(this.$refs.cardContent as Element, {
        suppressScrollX: true
      })

      this.$emit('ps-ready', this.ps)
    }
  }
}
</script>
