<template>
  <ul :class="{'menu-list':!isSubmenuList}">
    <aside-menu-item v-for="(item,index) in menu"
      @menu-click="menuClick"
      :is-secondary="isSecondary"
      :item="item"
      :key="index"/>
  </ul>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import AsideMenuItem from './AsideMenuItem.vue'

@Component({
  name: 'AsideMenuList',

  components: {
    AsideMenuItem
  }
})
export default class AsideMenuList extends Vue {
  @Prop({
    type: Boolean,
    default: false
  })
  isSubmenuList;

  @Prop({
    type: Boolean,
    default: false
  })
  isSecondary;

  @Prop({
    type: Array,
    default: () => []
  })
  menu;

  menuClick(item) {
    this.$emit('menu-click', item)
  }
}
</script>
