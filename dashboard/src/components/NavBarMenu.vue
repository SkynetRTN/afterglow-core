<template>
  <div @click="toggle" class="navbar-item has-dropdown has-dropdown-with-icons" :class="{ 'is-hoverable':isHoverable, 'is-active':isDropdownActive }">
    <a class="navbar-link is-arrowless">
      <slot/>
      <b-icon :icon="toggleDropdownIcon" custom-size="default"/>
    </a>
    <slot name="dropdown"/>
  </div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
@Component({
  name: 'NavBarMenu'
})
export default class NavBarMenu extends Vue {
  @Prop({
    type: Boolean,
    default: false
  })
  isHoverable;

  isDropdownActive = false;

  get toggleDropdownIcon() {
    return this.isDropdownActive ? 'chevron-up' : 'chevron-down'
  }

  created() {
    window.addEventListener('click', this.forceClose)
  }

  beforeDestroy() {
    window.removeEventListener('click', this.forceClose)
  }

  toggle() {
    if (!this.isHoverable) {
      this.isDropdownActive = !this.isDropdownActive
    }
  }

  forceClose(e) {
    if (!this.$el.contains(e.target)) {
      this.isDropdownActive = false
    }
  }
}
</script>
