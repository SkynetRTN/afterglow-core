<script lang="ts">
import { Vue, Component, Prop } from "vue-property-decorator";
import chunk from 'lodash/chunk'

@Component({
  name: 'Tiles'
})
export default class Tiles extends Vue {
  @Prop({
    type: Number,
    default: 5
  })
  maxPerRow;

  render(createElement) {
    if (this.$slots.default.length <= this.maxPerRow) {
      return this.renderAncestor(createElement, this.$slots.default)
    } else {
      return createElement('div', { attrs: { class: 'is-tiles-wrapper' } }, chunk(this.$slots.default, this.maxPerRow).map((group) => {
        return this.renderAncestor(createElement, group)
      }))
    }
  }

  renderAncestor(createElement, elements) {
    return createElement('div', { attrs: { class: 'tile is-ancestor' } }, elements.map((element) => {
      return createElement('div', { attrs: { class: 'tile is-parent' } }, [element])
    }))
  }
}
</script>
