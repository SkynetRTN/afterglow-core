<template>
  <li :class="{'is-active':isDropdownActive}">
    <component :is="componentIs" :to="itemTo" :href="itemHref" @click="menuClick" :title="componentTitle" :exact-active-class="componentActiveClass" :class="componentClass">
      <b-icon v-if="item.icon" :icon="item.icon" :class="{ 'has-update-mark' : item.updateMark }" custom-size="default"  />
      <span v-if="item.label" :class="{'menu-item-label':!!item.icon}">{{ item.label }}</span>
      <div v-if="hasSubmenuIcon" class="submenu-icon">
        <b-icon :icon="submenuIcon" custom-size="default"/>
      </div>
    </component>
    <aside-menu-list
        v-if="hasDropdown"
        :menu="item.menu"
        :isSubmenuList="true"/>
  </li>
</template>

<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import { mapState } from 'vuex'
import { UserModule } from '../store/modules/user'
import { AppModule } from '../store/modules/app'

@Component({
  name: 'AsideMenuItem',

  components: {
    AsideMenuList: () => import('./AsideMenuList.vue')
  },

  watch: {
    isAsideExpanded (newValue) {
      // TODO: FIX
      // if (!newValue) {
      //   this.isDropdownActive = false
      // }
    }
  }
})
export default class AsideMenuItem extends Vue {
  @Prop({
    type: Object,
    default: null
  })
  item;

  @Prop({
    type: Boolean,
    default: false
  })
  isSecondary;

  isDropdownActive = false;

  menuClick() {
    this.$emit('menu-click', this.item)

    if (this.hasDropdown) {
      this.isDropdownActive = (!this.isDropdownActive)

      if (!this.isSecondary && !AppModule.isAsideMobileExpanded) {
        this.$store.commit('asideStateToggle', true)
      }
    }
  }

  get componentIs() {
    return this.item.to ? 'router-link' : 'a'
  }

  get hasSubmenuIcon() {
    return this.hasDropdown || this.item.menuSecondary
  }

  get hasDropdown() {
    return !!this.item.menu
  }

  get submenuIcon() {
    if (this.item.menuSecondary) {
      return 'chevron-right'
    }
    return (this.isDropdownActive) ? 'minus' : 'plus'
  }

  get itemTo() {
    return this.item.to ? this.item.to : null
  }

  get itemHref() {
    return this.item.href ? this.item.href : null
  }

  get componentTitle() {
    return !this.isAsideExpanded && this.item.label ? this.item.label : null
  }

  get componentClass() {
    const c = {
      'has-icon': !!this.item.icon,
      'has-submenu-icon': this.hasSubmenuIcon
    }

    if (this.item.state) {
      c['is-state-' + this.item.state] = true
      c['is-hoverable'] = true
    }

    if (this.asideActiveForcedKey && this.item.menuSecondaryKey && this.asideActiveForcedKey === this.item.menuSecondaryKey) {
      c['is-active'] = true
    }

    return c
  }

  get componentActiveClass() {
    if (this.asideActiveForcedKey) {
      return null
    }
    return 'is-active'
  }

  get isAsideExpanded() {
    return AppModule.isAsideExpanded
  }

  get asideActiveForcedKey() {
    return AppModule.asideActiveForcedKey
  }
}
</script>
