import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import api from '@/api'

export const useQuestionStore = defineStore('question', () => {
  const questions = ref([])
  const currentQuestion = ref(null)
  const loading = ref(false)
  const filterOptions = ref({
    subject_id: null,
    chapter_id: null,
    question_type: null,
    difficulty: null,
    tag_ids: [],
    search: ''
  })

  const authStore = useAuthStore()

  // 获取题目列表
  async function fetchQuestions(params = {}) {
    loading.value = true
    try {
      const response = await api.get('/questions', { params })
      questions.value = response.data.questions
      return response.data
    } catch (error) {
      console.error('获取题目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取单个题目
  async function fetchQuestion(questionId) {
    loading.value = true
    try {
      const response = await api.get(`/questions/${questionId}`)
      currentQuestion.value = response.data
      return response.data
    } catch (error) {
      console.error('获取题目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 创建题目
  async function createQuestion(questionData) {
    try {
      const response = await api.post('/questions', questionData)
      return response.data
    } catch (error) {
      console.error('创建题目失败:', error)
      throw error
    }
  }

  // 更新题目
  async function updateQuestion(questionId, questionData) {
    try {
      const response = await api.put(`/questions/${questionId}`, questionData)
      return response.data
    } catch (error) {
      console.error('更新题目失败:', error)
      throw error
    }
  }

  // 删除题目
  async function deleteQuestion(questionId) {
    try {
      const response = await api.delete(`/questions/${questionId}`)
      return response.data
    } catch (error) {
      console.error('删除题目失败:', error)
      throw error
    }
  }

  // 批量导入题目
  async function batchImportQuestions(questionsData) {
    try {
      const response = await api.post('/questions/batch-import', {
        questions: questionsData
      })
      return response.data
    } catch (error) {
      console.error('批量导入失败:', error)
      throw error
    }
  }

  // 更新筛选条件
  function updateFilter(newFilter) {
    filterOptions.value = { ...filterOptions.value, ...newFilter }
  }

  // 清空筛选
  function clearFilter() {
    filterOptions.value = {
      subject_id: null,
      chapter_id: null,
      question_type: null,
      difficulty: null,
      tag_ids: [],
      search: ''
    }
  }

  // 计算属性：根据筛选条件获取题目
  const filteredQuestions = computed(() => {
    let filtered = [...questions.value]

    if (filterOptions.value.subject_id) {
      filtered = filtered.filter(q => q.subject_id === filterOptions.value.subject_id)
    }

    if (filterOptions.value.chapter_id) {
      filtered = filtered.filter(q => q.chapter_id === filterOptions.value.chapter_id)
    }

    if (filterOptions.value.question_type) {
      filtered = filtered.filter(q => q.question_type === filterOptions.value.question_type)
    }

    if (filterOptions.value.difficulty) {
      filtered = filtered.filter(q => q.difficulty === filterOptions.value.difficulty)
    }

    if (filterOptions.value.search) {
      const search = filterOptions.value.search.toLowerCase()
      filtered = filtered.filter(q =>
        q.title.toLowerCase().includes(search) ||
        q.content?.toLowerCase().includes(search)
      )
    }

    return filtered
  })

  // 获取题目类型选项
  async function fetchQuestionTypes() {
    try {
      const response = await api.get('/questions/types')
      return response.data.types
    } catch (error) {
      console.error('获取题目类型失败:', error)
      throw error
    }
  }

  // 获取难度选项
  async function fetchDifficulties() {
    try {
      const response = await api.get('/questions/difficulties')
      return response.data.difficulties
    } catch (error) {
      console.error('获取难度选项失败:', error)
      throw error
    }
  }

  return {
    questions,
    currentQuestion,
    loading,
    filterOptions,
    fetchQuestions,
    fetchQuestion,
    createQuestion,
    updateQuestion,
    deleteQuestion,
    batchImportQuestions,
    updateFilter,
    clearFilter,
    filteredQuestions,
    fetchQuestionTypes,
    fetchDifficulties
  }
})