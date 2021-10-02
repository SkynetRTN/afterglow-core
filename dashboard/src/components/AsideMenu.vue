<template>
  <aside
      v-show="isAsideVisible"
      class="aside is-placed-left"
      :class="{'is-expanded':isAsideExpanded || isSecondary, 'is-secondary':isSecondary}">
    <aside-tools :has-close="isSecondary" :icon="icon" @close="close">
      <span v-if="!isSecondary" class="brand">
        <template v-if="isAsideExpanded || isAsideMobileExpanded">
          <img src="../assets/logo-full.png" class="">
        </template>
        <template v-else>
          <img style="width: 35px;" src="../assets/logo.png" class="logo-no-text">
        </template>
      </span>
      <span v-else-if="label">{{ label }}</span>
    </aside-tools>
    <div ref="menuContainer" class="menu-container" @mouseenter="psUpdate">
      <div  class="menu is-menu-main" >
        <template v-for="(menuGroup, index) in menu" >
          <p class="menu-label" v-if="typeof menuGroup === 'string'" :key="index">{{ menuGroup }}</p>
          <aside-menu-list
            v-else
            :key="index"
            :is-secondary="isSecondary"
            @menu-click="menuClick"
            :menu="menuGroup"/>
        </template>
      </div>
    </div>
    <div class="menu is-menu-bottom">
      <aside-menu-list :menu="menuBottom" @menu-click="menuClick"/>
    </div>
  </aside>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import { mapState } from 'vuex'
import PerfectScrollbar from 'perfect-scrollbar'
import AsideTools from './AsideTools.vue'
import AsideMenuList from './AsideMenuList.vue'
import { UserModule } from '../store/modules/user'
import { AppModule } from '../store/modules/app'

@Component({
  name: 'AsideMenu',
  components: { AsideTools, AsideMenuList }
})
export default class AsideMenu extends Vue {
  private ps: PerfectScrollbar;
  
  @Prop({
    type: Array,
    default: () => []
  })
  menu;

  @Prop({
    type: Array,
    default: () => []
  })
  menuBottom;

  @Prop({
    type: Boolean,
    default: false
  })
  isSecondary;

  @Prop({
    type: String,
    default: null
  })
  label;

  @Prop({
    type: String,
    default: null
  })
  icon;

  get isAsideVisible() {
    return AppModule.isAsideVisible
  }

  get isAsideExpanded() {
    return AppModule.isAsideExpanded
  }

  get isAsideMobileExpanded() {
    return AppModule.isAsideMobileExpanded
  }

  mounted() {
    this.ps = new PerfectScrollbar(this.$refs.menuContainer as Element)
  }

  menuClick(item) {
    this.$emit('menu-click', item)
  }

  psUpdate() {
    if (this.ps) {
      this.ps.update()
    }
  }

  close() {
    this.$emit('close')
  }
}
</script>
